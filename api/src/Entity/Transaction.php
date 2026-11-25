<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'transactions')]
#[ORM\Index(name: 'idx_transactions_period', columns: ['user_id', 'date'])]
#[ORM\Index(name: 'fk_transaction_category', columns: ['category_id'])]
class Transaction
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\ManyToOne(targetEntity: User::class), ORM\JoinColumn(name: 'user_id', nullable: false, onDelete: 'CASCADE')]
    public User $owner;
    #[ORM\ManyToOne(targetEntity: Category::class), ORM\JoinColumn(name: 'category_id', nullable: false, onDelete: 'RESTRICT')]
    public Category $category;
    #[ORM\Column(type: 'date_immutable')]
    public \DateTimeImmutable $date;
    #[ORM\Column(type: 'decimal', precision: 15, scale: 2)]
    public string $amount;
    #[ORM\Column(length: 255, options: ['default' => ''])]
    public string $description = '';
}
